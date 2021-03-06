
# Things to control
# 1. model cfg
# 2. model weights loaded
# 3. model weight layer cutoff

import argparse
import time
from models import *
from utils import *
from parse import *
from datasets import *

def train(
        cfg,
        data_cfg,
        weights,
        cutoff,
        img_size=416,
        epochs=100,
        batch_size=16,
        accumulated_batches=1,
        multi_scale=False,
        freeze_backbone=False,
):


    # Pass in train data configuration
    train_path = parse_data_cfg(data_cfg)['train']

    checkpointPath = 'checkpoints/'
    # Initialize model
    model = Darknet(cfg, img_size)

    # Get dataloader
    dataloader = LoadImagesAndLabels(train_path, batch_size, img_size, multi_scale=multi_scale, augment=True)

    # Parameters
    lr0 = 0.001
    start_epoch = 0


    # Load all incoming weights [model, weights, cutoff]
    load_darknet_weights(model, weights, cutoff)


    # Transfer learning (train only YOLO layers)

    # Freeze all but YOLO layer
    for i, (name, p) in enumerate(model.named_parameters()):
        if(i<cutoff):
            p.requires_grad = True
        else:
            p.requires_grad = False

    # Freeze first X layers
    # for i, (name, p) in enumerate(model.named_parameters()):
    #     if int(name.split('.')[1]) < cutoff:  # if layer < 75

    # optimizer, the filter only passes in the parameter of the model that have grads
    optimizer = torch.optim.SGD(filter(lambda x: x.requires_grad, model.parameters()), lr=lr0, momentum=.9)

    # Train Loop
    for epoch in range(epochs):
        model.train()
        epoch += 1



        for i, (imgs, targets, _, _) in enumerate(dataloader):

            # Account for empty images
            numTargets = targets.shape[0]
            if(numTargets == 0):
                continue

            pred = model(imgs)

            # txs, tys, ths, tws, indicies [img in batch, cls, grid i, grid j]
            targetsAltered = getTargets(model, targets, pred)
            loss = lossCustom(pred, targetsAltered) # loss = lxy + lwh + lconf + lcls

            # Compute gradient
            loss.backward()

            # Accumulate gradient for x batches before optimizing
            # if ((i + 1) % accumulated_batches == 0) or (i == len(dataloader) - 1):
            optimizer.step()
            optimizer.zero_grad()

        # checkpoint stuff

        print("Epoch: {} Loss: {}".format(epoch, loss))
        # print(loss)
        # checkpoint = {'epoch': epoch,
        #               'model':  model.state_dict(),
        #               'optimizer': optimizer.state_dict()}
        # torch.save(checkpoint, checkpointPath + 'latest.pt')
        #
        # # save checkpoint (source...director)
        # if (epoch > 0) & (epoch % 5 == 0):
        #     os.system('cp ' + checkpointPath +  'latest.pt' + ' ' + 'weights/backup{}.pt'.format(epoch))
        #
        # # write the loss to results.txt (epoch __ loss)
        # with open('results.txt', 'a') as file:
        #     file.write("{} {} " + '\n'.format(epoch, loss))

# Main function
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--epochs', type=int, default=270, help='number of epochs')
    parser.add_argument('--batch-size', type=int, default=16, help='size of each image batch')
    parser.add_argument('--accumulated-batches', type=int, default=1, help='number of batches before optimizer step')

    parser.add_argument('--cfg', type=str, default='cfg/yolov3.cfg', help='cfg file path')
    parser.add_argument('--data-cfg', type=str, default='cfg/coco.data', help='coco.data file path')
    parser.add_argument('--weights', type=str, help='weights path')
    parser.add_argument('--cutoff', type=int, default=-1, help='layer cutoff (int)')

    parser.add_argument('--multi-scale', action='store_true', help='random image sizes per batch 320 - 608')
    parser.add_argument('--img-size', type=int, default=32 * 13, help='pixels')
    opt = parser.parse_args()
    print(opt, end='\n\n')

    train(
        opt.cfg,
        opt.data_cfg,
        opt.weights,
        cutoff=opt.cutoff,
        img_size=opt.img_size,
        epochs=opt.epochs,
        batch_size=opt.batch_size,
        accumulated_batches=opt.accumulated_batches,
        multi_scale=opt.multi_scale,
    )
